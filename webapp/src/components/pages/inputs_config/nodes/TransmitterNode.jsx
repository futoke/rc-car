// SPDX-FileCopyrightText: © 2023 OneEyeFPV oneeyefpv@gmail.com
// SPDX-License-Identifier: GPL-3.0-or-later
// SPDX-License-Identifier: FS-0.9-or-later

import React, {useCallback, useState} from 'react';
import {Transmitter} from "../../../../pbwrap";
import {SvgIcon} from "@mui/material";
import {TransmitterViewer} from "../../transmitters/TransmitterViewer";
import {BottomInput} from "../handles/BottomInput";
import {GenericInputNode} from "./GenericInputNode";
import {showError} from "../../../misc/notifications";
import {getTransmitters} from "../../../misc/server";


import {getNodeData} from "../misc/node-access";
import i18n from "../../../misc/I18n";


function TransmitterNode(node) {
    const [transmitterViewerOpen, setTransmitterViewerOpen] = useState(false);
    const [transmitter, setTransmitter] = useState(null);

    const onInspectOpen = useCallback(() => {
        let transmitterPort = getNodeData(node)?.port;

        if (!transmitterPort) {
            showError(`${i18n("error-msg-no-port")}`);
            return
        }

        (async () => {
            let transmitter = new Transmitter(); //mock the device in case we can't find it
            transmitter.setPort(transmitterPort);

            try {
                let transmittersList = await getTransmitters();
                let transmittersByPort = new Map(transmittersList.map((device) => [device.getPort(), device]));
                if (transmittersByPort.has(transmitterPort)) {
                    transmitter = transmittersByPort.get(transmitterPort);
                }
            } catch (e) {
                //ignore errors if we can't find it, we will mock it
            }

            setTransmitter(transmitter);
            setTransmitterViewerOpen(true);
        })()

    }, []);

    const handleViewerClose = useCallback(() => {
        setTransmitterViewerOpen(false);
    }, []);

    return (<GenericInputNode
            node={node}
            onInspectOpen={onInspectOpen}
            iconProps={{
                style: {marginTop: "-2px", marginBottom: "-5px"}
            }}
            labelProps={{
                style: {marginTop: "2px", marginBottom: "-1px"}
            }}
        >

            <BottomInput node={node} fieldName={"channels"}/>
            {transmitterViewerOpen && <TransmitterViewer transmitter={transmitter} open={transmitterViewerOpen}
                                                         onClose={handleViewerClose}/>}
        </GenericInputNode>);
}

function TransmitterIcon(props) {
    return <SvgIcon {...props} >
        <g fill="none">
            <path
                d="M24 0v24H0V0h24ZM12.593 23.258l-.011.002l-.071.035l-.02.004l-.014-.004l-.071-.035c-.01-.004-.019-.001-.024.005l-.004.01l-.017.428l.005.02l.01.013l.104.074l.015.004l.012-.004l.104-.074l.012-.016l.004-.017l-.017-.427c-.002-.01-.009-.017-.017-.018Zm.265-.113l-.013.002l-.185.093l-.01.01l-.003.011l.018.43l.005.012l.008.007l.201.093c.012.004.023 0 .029-.008l.004-.014l-.034-.614c-.003-.012-.01-.02-.02-.022Zm-.715.002a.023.023 0 0 0-.027.006l-.006.014l-.034.614c0 .012.007.02.017.024l.015-.002l.201-.093l.01-.008l.004-.011l.017-.43l-.003-.012l-.01-.01l-.184-.092Z"/>
            <path
                fill="#656565"
                d="M16 12a3 3 0 0 1 3 3v6c0 .552-.45 1-1.003 1H6a1 1 0 0 1-1-1v-6a3 3 0 0 1 3-3h8Zm-2 4h-4a1 1 0 0 0-.117 1.993L10 18h4a1 1 0 0 0 .117-1.993L14 16Zm-2-8c1.06 0 2.047.331 2.857.896a1 1 0 0 1-1.144 1.641A2.982 2.982 0 0 0 12 10c-.639 0-1.228.198-1.713.537a1 1 0 1 1-1.144-1.64A4.982 4.982 0 0 1 12 8Zm0-3c1.918 0 3.681.676 5.06 1.803a1 1 0 0 1-1.266 1.548A5.971 5.971 0 0 0 12 7c-1.44 0-2.758.506-3.792 1.35a1 1 0 1 1-1.265-1.549A7.971 7.971 0 0 1 12 5Zm0-3a10.96 10.96 0 0 1 7.209 2.691a1 1 0 0 1-1.311 1.51A8.961 8.961 0 0 0 12 4a8.95 8.95 0 0 0-5.9 2.205a1 1 0 0 1-1.312-1.51A10.961 10.961 0 0 1 12 2Z"
            />
        </g>
    </SvgIcon>;
}

TransmitterNode.type = "tx";
TransmitterNode.menuIcon = <TransmitterIcon/>

export default TransmitterNode;
